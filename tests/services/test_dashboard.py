"""
Unit tests for DashboardService business logic.
"""

import json
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.base import Base
from pybase.models.dashboard import Dashboard, DashboardMember, PermissionLevel
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.dashboard import (
    DashboardCreate,
    DashboardDuplicate,
    DashboardPermissionUpdate,
    DashboardSettings,
    DashboardShareRequest,
    DashboardUnshareRequest,
    DashboardUpdate,
    LayoutConfig,
)
from pybase.services.dashboard import DashboardService


@pytest.fixture
def dashboard_service():
    """Create an instance of DashboardService."""
    return DashboardService()


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add owner as workspace member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    return workspace


@pytest_asyncio.fixture
async def test_base(db_session: AsyncSession, test_workspace: Workspace) -> Base:
    """Create a test base."""
    base = Base(
        workspace_id=test_workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def test_dashboard(
    db_session: AsyncSession,
    test_base: Base,
    test_user: User,
) -> Dashboard:
    """Create a test dashboard."""
    dashboard = Dashboard(
        base_id=test_base.id,
        created_by_id=test_user.id,
        name="Test Dashboard",
        description="Test Description",
        is_default=False,
        is_personal=False,
        is_public=False,
        is_locked=False,
        layout_config="{}",
        settings="{}",
        global_filters="[]",
    )
    db_session.add(dashboard)
    await db_session.commit()
    await db_session.refresh(dashboard)
    return dashboard


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession, test_workspace: Workspace) -> User:
    """Create a second test user with workspace access."""
    user = User(
        email=f"second-user-{uuid4()}@test.com",
        username=f"seconduser-{uuid4()}",
        hashed_password="hashedpass",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Add as workspace member
    member = WorkspaceMember(
        workspace_id=test_workspace.id,
        user_id=user.id,
        role=WorkspaceRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()

    return user


class TestCreateDashboard:
    """Test dashboard creation."""

    @pytest.mark.asyncio
    async def test_create_basic_dashboard(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
    ):
        """Test creating a basic dashboard."""
        dashboard_data = DashboardCreate(
            base_id=test_base.id,
            name="New Dashboard",
            description="Test dashboard",
        )

        dashboard = await dashboard_service.create_dashboard(
            db_session,
            test_user.id,
            dashboard_data,
        )

        assert dashboard.id is not None
        assert dashboard.name == "New Dashboard"
        assert dashboard.description == "Test dashboard"
        assert dashboard.base_id == test_base.id
        assert dashboard.created_by_id == test_user.id
        assert dashboard.is_default is False
        assert dashboard.is_personal is False

    @pytest.mark.asyncio
    async def test_create_dashboard_with_layout_config(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
    ):
        """Test creating a dashboard with layout configuration."""
        layout_config = LayoutConfig(
            grid_columns=12,
            row_height=60,
            widgets=[],
        )

        dashboard_data = DashboardCreate(
            base_id=test_base.id,
            name="Dashboard with Layout",
            layout_config=layout_config,
        )

        dashboard = await dashboard_service.create_dashboard(
            db_session,
            test_user.id,
            dashboard_data,
        )

        assert dashboard.layout_config is not None
        config = dashboard.get_layout_config_dict()
        assert config["grid_columns"] == 12
        assert config["row_height"] == 60

    @pytest.mark.asyncio
    async def test_create_default_dashboard_unsets_others(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
        test_dashboard: Dashboard,
    ):
        """Test that creating a default dashboard unsets other defaults."""
        # Set existing dashboard as default
        test_dashboard.is_default = True
        await db_session.commit()
        await db_session.refresh(test_dashboard)
        assert test_dashboard.is_default is True

        # Create new default dashboard
        dashboard_data = DashboardCreate(
            base_id=test_base.id,
            name="New Default Dashboard",
            is_default=True,
        )

        new_dashboard = await dashboard_service.create_dashboard(
            db_session,
            test_user.id,
            dashboard_data,
        )

        # Refresh old dashboard
        await db_session.refresh(test_dashboard)

        assert new_dashboard.is_default is True
        assert test_dashboard.is_default is False

    @pytest.mark.asyncio
    async def test_create_dashboard_without_base_access_fails(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
    ):
        """Test that creating dashboard without base access fails."""
        # Create user without workspace access
        unauthorized_user = User(
            email=f"unauthorized-{uuid4()}@test.com",
            username=f"unauthorized-{uuid4()}",
            hashed_password="hashedpass",
        )
        db_session.add(unauthorized_user)
        await db_session.commit()
        await db_session.refresh(unauthorized_user)

        dashboard_data = DashboardCreate(
            base_id=test_base.id,
            name="Unauthorized Dashboard",
        )

        with pytest.raises(PermissionDeniedError):
            await dashboard_service.create_dashboard(
                db_session,
                unauthorized_user.id,
                dashboard_data,
            )


class TestGetDashboard:
    """Test dashboard retrieval."""

    @pytest.mark.asyncio
    async def test_get_dashboard_by_id(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test retrieving a dashboard by ID."""
        dashboard = await dashboard_service.get_dashboard_by_id(
            db_session,
            test_dashboard.id,
            test_user.id,
        )

        assert dashboard.id == test_dashboard.id
        assert dashboard.name == test_dashboard.name
        assert dashboard.last_viewed_at is not None

    @pytest.mark.asyncio
    async def test_get_personal_dashboard_as_creator(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
    ):
        """Test that creator can access personal dashboard."""
        # Create personal dashboard
        personal_dashboard = Dashboard(
            base_id=test_base.id,
            created_by_id=test_user.id,
            name="Personal Dashboard",
            is_personal=True,
            layout_config="{}",
            settings="{}",
            global_filters="[]",
        )
        db_session.add(personal_dashboard)
        await db_session.commit()
        await db_session.refresh(personal_dashboard)

        dashboard = await dashboard_service.get_dashboard_by_id(
            db_session,
            personal_dashboard.id,
            test_user.id,
        )

        assert dashboard.id == personal_dashboard.id
        assert dashboard.is_personal is True

    @pytest.mark.asyncio
    async def test_get_personal_dashboard_as_other_user_fails(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
        second_user: User,
    ):
        """Test that non-creator cannot access personal dashboard."""
        # Create personal dashboard
        personal_dashboard = Dashboard(
            base_id=test_base.id,
            created_by_id=test_user.id,
            name="Personal Dashboard",
            is_personal=True,
            layout_config="{}",
            settings="{}",
            global_filters="[]",
        )
        db_session.add(personal_dashboard)
        await db_session.commit()
        await db_session.refresh(personal_dashboard)

        with pytest.raises(PermissionDeniedError):
            await dashboard_service.get_dashboard_by_id(
                db_session,
                personal_dashboard.id,
                second_user.id,
            )

    @pytest.mark.asyncio
    async def test_get_nonexistent_dashboard_fails(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_user: User,
    ):
        """Test that getting nonexistent dashboard fails."""
        fake_id = str(uuid4())

        with pytest.raises(NotFoundError):
            await dashboard_service.get_dashboard_by_id(
                db_session,
                fake_id,
                test_user.id,
            )


class TestListDashboards:
    """Test dashboard listing."""

    @pytest.mark.asyncio
    async def test_list_dashboards_for_base(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
        test_dashboard: Dashboard,
    ):
        """Test listing dashboards for a base."""
        dashboards, total = await dashboard_service.list_dashboards(
            db_session,
            test_base.id,
            test_user.id,
        )

        assert total >= 1
        assert len(dashboards) >= 1
        assert any(d.id == test_dashboard.id for d in dashboards)

    @pytest.mark.asyncio
    async def test_list_dashboards_excludes_personal_from_others(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
        second_user: User,
    ):
        """Test that listing excludes personal dashboards from other users."""
        # Create personal dashboard for test_user
        personal_dashboard = Dashboard(
            base_id=test_base.id,
            created_by_id=test_user.id,
            name="Personal Dashboard",
            is_personal=True,
            layout_config="{}",
            settings="{}",
            global_filters="[]",
        )
        db_session.add(personal_dashboard)
        await db_session.commit()

        # List as second_user
        dashboards, total = await dashboard_service.list_dashboards(
            db_session,
            test_base.id,
            second_user.id,
        )

        # Personal dashboard should not appear
        assert not any(d.id == personal_dashboard.id for d in dashboards)

    @pytest.mark.asyncio
    async def test_list_dashboards_default_first(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
    ):
        """Test that default dashboard appears first in list."""
        # Create multiple dashboards with one default
        dashboard1 = Dashboard(
            base_id=test_base.id,
            created_by_id=test_user.id,
            name="A Dashboard",
            is_default=False,
            layout_config="{}",
            settings="{}",
            global_filters="[]",
        )
        dashboard2 = Dashboard(
            base_id=test_base.id,
            created_by_id=test_user.id,
            name="B Dashboard",
            is_default=True,
            layout_config="{}",
            settings="{}",
            global_filters="[]",
        )
        db_session.add(dashboard1)
        db_session.add(dashboard2)
        await db_session.commit()

        dashboards, total = await dashboard_service.list_dashboards(
            db_session,
            test_base.id,
            test_user.id,
        )

        # Default dashboard should be first
        assert dashboards[0].is_default is True


class TestUpdateDashboard:
    """Test dashboard updates."""

    @pytest.mark.asyncio
    async def test_update_dashboard_name(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test updating dashboard name."""
        update_data = DashboardUpdate(name="Updated Dashboard Name")

        updated = await dashboard_service.update_dashboard(
            db_session,
            test_dashboard.id,
            test_user.id,
            update_data,
        )

        assert updated.name == "Updated Dashboard Name"

    @pytest.mark.asyncio
    async def test_update_dashboard_settings(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test updating dashboard settings."""
        settings = DashboardSettings(
            auto_refresh_enabled=True,
            refresh_interval=300,
            theme="dark",
        )

        update_data = DashboardUpdate(settings=settings)

        updated = await dashboard_service.update_dashboard(
            db_session,
            test_dashboard.id,
            test_user.id,
            update_data,
        )

        settings_dict = updated.get_settings_dict()
        assert settings_dict["auto_refresh_enabled"] is True
        assert settings_dict["refresh_interval"] == 300
        assert settings_dict["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_update_locked_dashboard_fails_for_non_creator(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
        second_user: User,
    ):
        """Test that updating locked dashboard fails for non-creator."""
        # Create locked dashboard
        locked_dashboard = Dashboard(
            base_id=test_base.id,
            created_by_id=test_user.id,
            name="Locked Dashboard",
            is_locked=True,
            layout_config="{}",
            settings="{}",
            global_filters="[]",
        )
        db_session.add(locked_dashboard)
        await db_session.commit()
        await db_session.refresh(locked_dashboard)

        update_data = DashboardUpdate(name="Attempted Update")

        with pytest.raises(PermissionDeniedError):
            await dashboard_service.update_dashboard(
                db_session,
                locked_dashboard.id,
                second_user.id,
                update_data,
            )


class TestDeleteDashboard:
    """Test dashboard deletion."""

    @pytest.mark.asyncio
    async def test_delete_dashboard_as_creator(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test deleting dashboard as creator."""
        await dashboard_service.delete_dashboard(
            db_session,
            test_dashboard.id,
            test_user.id,
        )

        # Refresh to get updated state
        await db_session.refresh(test_dashboard)
        assert test_dashboard.is_deleted is True

    @pytest.mark.asyncio
    async def test_delete_dashboard_as_workspace_owner(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_dashboard: Dashboard,
        test_workspace: Workspace,
    ):
        """Test deleting dashboard as workspace owner."""
        await dashboard_service.delete_dashboard(
            db_session,
            test_dashboard.id,
            test_workspace.owner_id,
        )

        await db_session.refresh(test_dashboard)
        assert test_dashboard.is_deleted is True

    @pytest.mark.asyncio
    async def test_delete_dashboard_as_non_creator_fails(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_dashboard: Dashboard,
        second_user: User,
    ):
        """Test that non-creator cannot delete dashboard."""
        with pytest.raises(PermissionDeniedError):
            await dashboard_service.delete_dashboard(
                db_session,
                test_dashboard.id,
                second_user.id,
            )


class TestDuplicateDashboard:
    """Test dashboard duplication."""

    @pytest.mark.asyncio
    async def test_duplicate_dashboard(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test duplicating a dashboard."""
        duplicate_data = DashboardDuplicate(
            name="Duplicated Dashboard",
            include_layout=True,
            include_settings=True,
            include_filters=True,
        )

        duplicate = await dashboard_service.duplicate_dashboard(
            db_session,
            test_dashboard.id,
            test_user.id,
            duplicate_data,
        )

        assert duplicate.id != test_dashboard.id
        assert duplicate.name == "Duplicated Dashboard"
        assert duplicate.base_id == test_dashboard.base_id
        assert duplicate.created_by_id == test_user.id
        assert duplicate.is_default is False
        assert duplicate.is_personal is True


class TestShareDashboard:
    """Test dashboard sharing."""

    @pytest.mark.asyncio
    async def test_share_dashboard_with_users(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_dashboard: Dashboard,
        test_user: User,
        second_user: User,
    ):
        """Test sharing dashboard with users."""
        share_request = DashboardShareRequest(
            user_ids=[second_user.id],
            permission=PermissionLevel.VIEW,
        )

        members = await dashboard_service.share_dashboard(
            db_session,
            test_dashboard.id,
            test_user.id,
            share_request,
        )

        assert len(members) == 1
        assert members[0].user_id == second_user.id
        assert members[0].permission == PermissionLevel.VIEW.value

    @pytest.mark.asyncio
    async def test_share_personal_dashboard_fails(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_base: Base,
        test_user: User,
        second_user: User,
    ):
        """Test that sharing personal dashboard fails."""
        # Create personal dashboard
        personal_dashboard = Dashboard(
            base_id=test_base.id,
            created_by_id=test_user.id,
            name="Personal Dashboard",
            is_personal=True,
            layout_config="{}",
            settings="{}",
            global_filters="[]",
        )
        db_session.add(personal_dashboard)
        await db_session.commit()
        await db_session.refresh(personal_dashboard)

        share_request = DashboardShareRequest(
            user_ids=[second_user.id],
            permission=PermissionLevel.VIEW,
        )

        with pytest.raises(PermissionDeniedError):
            await dashboard_service.share_dashboard(
                db_session,
                personal_dashboard.id,
                test_user.id,
                share_request,
            )

    @pytest.mark.asyncio
    async def test_generate_share_token(
        self,
        db_session: AsyncSession,
        dashboard_service: DashboardService,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test generating a share token."""
        token = await dashboard_service.generate_share_token(
            db_session,
            test_dashboard.id,
            test_user.id,
        )

        assert token is not None
        assert len(token) > 0

        # Verify we can get dashboard by token
        retrieved = await dashboard_service.get_dashboard_by_share_token(
            db_session,
            token,
        )

        assert retrieved.id == test_dashboard.id
