"""Dashboard service for business logic."""

import json
import secrets
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.base import Base
from pybase.models.dashboard import Dashboard, DashboardMember, PermissionLevel
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.dashboard import (
    DashboardCreate,
    DashboardDuplicate,
    DashboardPermissionUpdate,
    DashboardShareRequest,
    DashboardUnshareRequest,
    DashboardUpdate,
)


class DashboardService:
    """Service for dashboard operations."""

    async def create_dashboard(
        self,
        db: AsyncSession,
        user_id: str,
        dashboard_data: DashboardCreate,
    ) -> Dashboard:
        """Create a new dashboard for a base.

        Args:
            db: Database session
            user_id: User ID creating the dashboard
            dashboard_data: Dashboard creation data

        Returns:
            Created dashboard

        Raises:
            NotFoundError: If base not found
            PermissionDeniedError: If user doesn't have access

        """
        # Check if base exists and user has access
        base = await self._get_base_with_access(db, str(dashboard_data.base_id), user_id)

        # If setting as default, unset other defaults
        if dashboard_data.is_default:
            await self._unset_default_dashboards(db, str(dashboard_data.base_id))

        # Serialize configurations to JSON
        layout_config = None
        if dashboard_data.layout_config:
            layout_config = json.dumps(dashboard_data.layout_config.model_dump(mode="json"))

        settings = None
        if dashboard_data.settings:
            settings = json.dumps(dashboard_data.settings.model_dump(mode="json"))

        global_filters = json.dumps(
            [f.model_dump(mode="json") for f in dashboard_data.global_filters]
        )

        # Create dashboard
        dashboard = Dashboard(
            base_id=str(dashboard_data.base_id),
            created_by_id=user_id,
            name=dashboard_data.name,
            description=dashboard_data.description,
            is_default=dashboard_data.is_default,
            is_personal=dashboard_data.is_personal,
            is_public=dashboard_data.is_public,
            is_locked=dashboard_data.is_locked,
            color=dashboard_data.color,
            icon=dashboard_data.icon,
            template_id=dashboard_data.template_id,
            layout_config=layout_config or "{}",
            settings=settings or "{}",
            global_filters=global_filters,
        )
        db.add(dashboard)
        await db.commit()
        await db.refresh(dashboard)

        return dashboard

    async def get_dashboard_by_id(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
    ) -> Dashboard:
        """Get a dashboard by ID, checking user access.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID requesting access

        Returns:
            Dashboard

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have access

        """
        dashboard = await db.get(Dashboard, dashboard_id)
        if not dashboard or dashboard.is_deleted:
            raise NotFoundError("Dashboard not found")

        # Check user access to base
        await self._get_base_with_access(db, dashboard.base_id, user_id)

        # Personal dashboards are only visible to creator
        if dashboard.is_personal and dashboard.created_by_id != user_id:
            raise PermissionDeniedError("This is a personal dashboard")

        # Update last viewed timestamp
        dashboard.update_last_viewed()
        await db.commit()

        return dashboard

    async def list_dashboards(
        self,
        db: AsyncSession,
        base_id: UUID,
        user_id: str,
        include_personal: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Dashboard], int]:
        """List dashboards for a base.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID
            include_personal: Include personal dashboards (only user's own)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (dashboards, total count)

        """
        # Check user access to base
        await self._get_base_with_access(db, str(base_id), user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [
            Dashboard.base_id == str(base_id),
            Dashboard.deleted_at.is_(None),
        ]

        # Personal dashboards filter
        if include_personal:
            # Show non-personal dashboards OR user's personal dashboards
            conditions.append(
                or_(
                    Dashboard.is_personal.is_(False),
                    Dashboard.created_by_id == user_id,
                )
            )
        else:
            conditions.append(Dashboard.is_personal.is_(False))

        # Count query
        count_query = select(func.count()).select_from(Dashboard).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query - order by default first, then name
        query = (
            select(Dashboard)
            .where(*conditions)
            .order_by(Dashboard.is_default.desc(), Dashboard.name)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        dashboards = result.scalars().all()

        return list(dashboards), total

    async def update_dashboard(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
        dashboard_data: DashboardUpdate,
    ) -> Dashboard:
        """Update a dashboard.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID making request
            dashboard_data: Dashboard update data

        Returns:
            Updated dashboard

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have edit permission

        """
        dashboard = await self.get_dashboard_by_id(db, dashboard_id, user_id)

        # Check edit permission
        await self._check_edit_permission(db, dashboard, user_id)

        # Update basic fields
        if dashboard_data.name is not None:
            dashboard.name = dashboard_data.name
        if dashboard_data.description is not None:
            dashboard.description = dashboard_data.description
        if dashboard_data.color is not None:
            dashboard.color = dashboard_data.color
        if dashboard_data.icon is not None:
            dashboard.icon = dashboard_data.icon

        # Update visibility flags
        if dashboard_data.is_personal is not None:
            dashboard.is_personal = dashboard_data.is_personal
        if dashboard_data.is_public is not None:
            dashboard.is_public = dashboard_data.is_public
        if dashboard_data.is_locked is not None:
            dashboard.is_locked = dashboard_data.is_locked

        # Handle default flag
        if dashboard_data.is_default is not None and dashboard_data.is_default:
            await self._unset_default_dashboards(db, dashboard.base_id)
            dashboard.is_default = True
        elif dashboard_data.is_default is not None:
            dashboard.is_default = False

        # Update configuration fields
        if dashboard_data.layout_config is not None:
            dashboard.layout_config = json.dumps(
                dashboard_data.layout_config.model_dump(mode="json")
            )
        if dashboard_data.settings is not None:
            dashboard.settings = json.dumps(dashboard_data.settings.model_dump(mode="json"))
        if dashboard_data.global_filters is not None:
            dashboard.global_filters = json.dumps(
                [f.model_dump(mode="json") for f in dashboard_data.global_filters]
            )

        await db.commit()
        await db.refresh(dashboard)

        return dashboard

    async def delete_dashboard(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
    ) -> None:
        """Delete (soft delete) a dashboard.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID making request

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have permission

        """
        dashboard = await self.get_dashboard_by_id(db, dashboard_id, user_id)

        # Only creator or base owner can delete
        base = await self._get_base_with_access(db, dashboard.base_id, user_id)
        workspace = await self._get_workspace(db, base.workspace_id)

        is_creator = dashboard.created_by_id == user_id
        is_workspace_owner = workspace.owner_id == user_id

        if not (is_creator or is_workspace_owner):
            raise PermissionDeniedError("Only dashboard creator or workspace owner can delete")

        dashboard.is_deleted = True
        await db.commit()

    async def duplicate_dashboard(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
        duplicate_data: DashboardDuplicate,
    ) -> Dashboard:
        """Duplicate an existing dashboard.

        Args:
            db: Database session
            dashboard_id: Dashboard ID to duplicate
            user_id: User ID making request
            duplicate_data: Duplication options

        Returns:
            Duplicated dashboard

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have access

        """
        source_dashboard = await self.get_dashboard_by_id(db, dashboard_id, user_id)

        # Create new dashboard with copied data
        new_dashboard = Dashboard(
            base_id=source_dashboard.base_id,
            created_by_id=user_id,
            name=duplicate_data.name,
            description=source_dashboard.description,
            is_default=False,  # Duplicates are never default
            is_personal=True,  # Duplicates are personal by default
            is_public=False,
            is_locked=False,
            color=source_dashboard.color,
            icon=source_dashboard.icon,
            template_id=source_dashboard.template_id,
            layout_config=(
                source_dashboard.layout_config if duplicate_data.include_layout else "{}"
            ),
            settings=source_dashboard.settings if duplicate_data.include_settings else "{}",
            global_filters=(
                source_dashboard.global_filters if duplicate_data.include_filters else "[]"
            ),
        )
        db.add(new_dashboard)
        await db.commit()
        await db.refresh(new_dashboard)

        return new_dashboard

    async def share_dashboard(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
        share_request: DashboardShareRequest,
    ) -> list[DashboardMember]:
        """Share a dashboard with users.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID making request
            share_request: Share request data

        Returns:
            List of created dashboard members

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have permission

        """
        dashboard = await self.get_dashboard_by_id(db, dashboard_id, user_id)

        # Only creator can share
        if dashboard.created_by_id != user_id:
            raise PermissionDeniedError("Only dashboard creator can share")

        # Cannot share personal dashboards
        if dashboard.is_personal:
            raise PermissionDeniedError("Cannot share personal dashboards")

        members = []
        for share_user_id in share_request.user_ids:
            # Check if user already has access
            existing = await self._get_dashboard_member(db, dashboard_id, str(share_user_id))
            if existing:
                continue

            # Create dashboard member
            member = DashboardMember(
                dashboard_id=dashboard_id,
                user_id=str(share_user_id),
                permission=share_request.permission.value,
                shared_by_id=user_id,
            )
            db.add(member)
            members.append(member)

        await db.commit()
        for member in members:
            await db.refresh(member)

        return members

    async def unshare_dashboard(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
        unshare_request: DashboardUnshareRequest,
    ) -> None:
        """Remove dashboard access from users.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID making request
            unshare_request: Unshare request data

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have permission

        """
        dashboard = await self.get_dashboard_by_id(db, dashboard_id, user_id)

        # Only creator can unshare
        if dashboard.created_by_id != user_id:
            raise PermissionDeniedError("Only dashboard creator can unshare")

        for unshare_user_id in unshare_request.user_ids:
            member = await self._get_dashboard_member(db, dashboard_id, str(unshare_user_id))
            if member:
                await db.delete(member)

        await db.commit()

    async def update_member_permission(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
        permission_update: DashboardPermissionUpdate,
    ) -> DashboardMember:
        """Update a dashboard member's permission.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID making request
            permission_update: Permission update data

        Returns:
            Updated dashboard member

        Raises:
            NotFoundError: If dashboard or member not found
            PermissionDeniedError: If user doesn't have permission

        """
        dashboard = await self.get_dashboard_by_id(db, dashboard_id, user_id)

        # Only creator can update permissions
        if dashboard.created_by_id != user_id:
            raise PermissionDeniedError("Only dashboard creator can update permissions")

        member = await self._get_dashboard_member(
            db, dashboard_id, str(permission_update.user_id)
        )
        if not member:
            raise NotFoundError("Dashboard member not found")

        member.permission = permission_update.permission.value
        await db.commit()
        await db.refresh(member)

        return member

    async def generate_share_token(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
    ) -> str:
        """Generate a public share token for a dashboard.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID making request

        Returns:
            Generated share token

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have permission

        """
        dashboard = await self.get_dashboard_by_id(db, dashboard_id, user_id)

        # Only creator can generate share token
        if dashboard.created_by_id != user_id:
            raise PermissionDeniedError("Only dashboard creator can generate share token")

        # Generate secure token
        if not dashboard.share_token:
            dashboard.share_token = secrets.token_urlsafe(32)
            await db.commit()
            await db.refresh(dashboard)

        return dashboard.share_token

    async def revoke_share_token(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
    ) -> None:
        """Revoke a dashboard's public share token.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID making request

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have permission

        """
        dashboard = await self.get_dashboard_by_id(db, dashboard_id, user_id)

        # Only creator can revoke share token
        if dashboard.created_by_id != user_id:
            raise PermissionDeniedError("Only dashboard creator can revoke share token")

        dashboard.share_token = None
        await db.commit()

    async def get_dashboard_by_share_token(
        self,
        db: AsyncSession,
        share_token: str,
    ) -> Dashboard:
        """Get a dashboard by its public share token.

        Args:
            db: Database session
            share_token: Share token

        Returns:
            Dashboard

        Raises:
            NotFoundError: If dashboard not found

        """
        query = select(Dashboard).where(
            Dashboard.share_token == share_token,
            Dashboard.deleted_at.is_(None),
        )
        result = await db.execute(query)
        dashboard = result.scalar_one_or_none()

        if not dashboard:
            raise NotFoundError("Dashboard not found")

        return dashboard

    # Helper methods

    async def _get_base_with_access(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
    ) -> Base:
        """Get base and check user has access.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID

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

    async def _get_dashboard_member(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
    ) -> Optional[DashboardMember]:
        """Get dashboard member.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID

        Returns:
            DashboardMember or None

        """
        query = select(DashboardMember).where(
            DashboardMember.dashboard_id == dashboard_id,
            DashboardMember.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _unset_default_dashboards(
        self,
        db: AsyncSession,
        base_id: str,
    ) -> None:
        """Unset all default dashboards for a base.

        Args:
            db: Database session
            base_id: Base ID

        """
        query = select(Dashboard).where(
            Dashboard.base_id == base_id,
            Dashboard.is_default.is_(True),
            Dashboard.deleted_at.is_(None),
        )
        result = await db.execute(query)
        dashboards = result.scalars().all()

        for dashboard in dashboards:
            dashboard.is_default = False

        await db.commit()

    async def _check_edit_permission(
        self,
        db: AsyncSession,
        dashboard: Dashboard,
        user_id: str,
    ) -> None:
        """Check if user has edit permission for dashboard.

        Args:
            db: Database session
            dashboard: Dashboard
            user_id: User ID

        Raises:
            PermissionDeniedError: If user doesn't have edit permission

        """
        # Creator always has edit permission
        if dashboard.created_by_id == user_id:
            return

        # Check if dashboard is locked
        if dashboard.is_locked:
            raise PermissionDeniedError("Dashboard is locked")

        # Check dashboard member permission
        member = await self._get_dashboard_member(db, dashboard.id, user_id)
        if member and member.can_edit:
            return

        raise PermissionDeniedError("You don't have permission to edit this dashboard")
