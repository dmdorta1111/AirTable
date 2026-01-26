"""Unit tests for ConstraintService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.field import Field
from pybase.models.table import Table
from pybase.models.unique_constraint import UniqueConstraint, UniqueConstraintStatus
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.constraint import UniqueConstraintCreate, UniqueConstraintUpdate
from pybase.services.constraint import ConstraintService


@pytest.fixture
def constraint_service():
    """Create a ConstraintService instance."""
    return ConstraintService()


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.get = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_workspace():
    """Create a mock workspace."""
    workspace = MagicMock(spec=Workspace)
    workspace.id = str(uuid4())
    workspace.owner_id = str(uuid4())
    workspace.is_deleted = False
    return workspace


@pytest.fixture
def mock_base(mock_workspace):
    """Create a mock base."""
    base = MagicMock()
    base.id = str(uuid4())
    base.workspace_id = mock_workspace.id
    base.is_deleted = False
    return base


@pytest.fixture
def mock_table(mock_base):
    """Create a mock table."""
    table = MagicMock(spec=Table)
    table.id = str(uuid4())
    table.base_id = mock_base.id
    table.is_deleted = False
    return table


@pytest.fixture
def mock_field(mock_table):
    """Create a mock field."""
    field = MagicMock(spec=Field)
    field.id = str(uuid4())
    field.table_id = mock_table.id
    field.is_deleted = False
    # Add the unique_constraints relationship as a list
    field.unique_constraints = []
    return field


@pytest.fixture
def mock_workspace_member(mock_workspace):
    """Create a mock workspace member."""
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = mock_workspace.id
    member.user_id = str(uuid4())
    member.role = WorkspaceRole.ADMIN
    return member


@pytest.fixture
def mock_constraint(mock_field):
    """Create a mock constraint."""
    constraint = MagicMock(spec=UniqueConstraint)
    constraint.id = str(uuid4())
    constraint.field_id = mock_field.id
    constraint.status = UniqueConstraintStatus.ACTIVE.value
    constraint.case_sensitive = True
    constraint.error_message = None
    constraint.created_at = datetime.now()
    constraint.updated_at = datetime.now()
    return constraint


class TestConstraintServiceCreate:
    """Test ConstraintService.create_constraint."""

    @pytest.mark.asyncio
    async def test_create_constraint_success(
        self,
        constraint_service,
        mock_db,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
        mock_workspace_member,
    ):
        """Test successful constraint creation."""
        # Setup mock returns
        mock_db.get.return_value = mock_field

        # Mock query result for existing constraint check
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock query result for workspace member check
        def execute_side_effect(query):
            result = MagicMock()
            if "WorkspaceMember" in str(query):
                result.scalar_one_or_none.return_value = mock_workspace_member
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = execute_side_effect

        # Create constraint data
        constraint_data = UniqueConstraintCreate(
            field_id=mock_field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
            case_sensitive=True,
            error_message="Value must be unique",
        )

        # Mock UniqueConstraint model to avoid SQLAlchemy relationship issues
        with (
            patch("pybase.services.constraint.UniqueConstraint", autospec=True) as mock_constraint_model,
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service,
                "_get_workspace_member",
                return_value=mock_workspace_member,
            ),
            patch.object(
                constraint_service, "_get_constraint_by_field", return_value=None
            ),
        ):
            mock_constraint_instance = MagicMock()
            mock_constraint_instance.id = str(uuid4())
            mock_constraint_model.return_value = mock_constraint_instance

            result = await constraint_service.create_constraint(
                mock_db, mock_workspace_member.user_id, constraint_data
            )

            # Verify constraint was created
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_constraint_field_not_found(
        self, constraint_service, mock_db
    ):
        """Test constraint creation with non-existent field."""
        mock_db.get.return_value = None

        constraint_data = UniqueConstraintCreate(
            field_id=str(uuid4()),
            status=UniqueConstraintStatus.ACTIVE.value,
        )

        with pytest.raises(Exception) as exc_info:
            await constraint_service.create_constraint(
                mock_db, str(uuid4()), constraint_data
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_constraint_field_deleted(
        self, constraint_service, mock_db, mock_field
    ):
        """Test constraint creation with deleted field."""
        mock_field.is_deleted = True
        mock_db.get.return_value = mock_field

        constraint_data = UniqueConstraintCreate(
            field_id=mock_field.id,
            status=UniqueConstraintStatus.ACTIVE.value,
        )

        with pytest.raises(Exception) as exc_info:
            await constraint_service.create_constraint(
                mock_db, str(uuid4()), constraint_data
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_constraint_permission_denied(
        self,
        constraint_service,
        mock_db,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
    ):
        """Test constraint creation without workspace access."""
        mock_db.get.return_value = mock_field

        with (
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service, "_get_workspace_member", return_value=None
            ),
        ):
            constraint_data = UniqueConstraintCreate(
                field_id=mock_field.id,
                status=UniqueConstraintStatus.ACTIVE.value,
            )

            with pytest.raises(Exception) as exc_info:
                await constraint_service.create_constraint(
                    mock_db, str(uuid4()), constraint_data
                )

            assert "access" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_constraint_already_exists(
        self,
        constraint_service,
        mock_db,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
        mock_workspace_member,
        mock_constraint,
    ):
        """Test constraint creation when constraint already exists."""
        mock_db.get.return_value = mock_field

        with (
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service,
                "_get_workspace_member",
                return_value=mock_workspace_member,
            ),
            patch.object(
                constraint_service,
                "_get_constraint_by_field",
                return_value=mock_constraint,
            ),
        ):
            constraint_data = UniqueConstraintCreate(
                field_id=mock_field.id,
                status=UniqueConstraintStatus.ACTIVE.value,
            )

            with pytest.raises(Exception) as exc_info:
                await constraint_service.create_constraint(
                    mock_db, mock_workspace_member.user_id, constraint_data
                )

            assert "already exists" in str(exc_info.value).lower()


class TestConstraintServiceGetById:
    """Test ConstraintService.get_constraint_by_id."""

    @pytest.mark.asyncio
    async def test_get_constraint_by_id_success(
        self,
        constraint_service,
        mock_db,
        mock_constraint,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
        mock_workspace_member,
    ):
        """Test successful constraint retrieval by ID."""
        mock_db.get.return_value = mock_constraint

        with (
            patch.object(
                constraint_service, "_get_field", return_value=mock_field
            ),
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service,
                "_get_workspace_member",
                return_value=mock_workspace_member,
            ),
        ):
            result = await constraint_service.get_constraint_by_id(
                mock_db, mock_constraint.id, mock_workspace_member.user_id
            )

            assert result == mock_constraint

    @pytest.mark.asyncio
    async def test_get_constraint_by_id_not_found(
        self, constraint_service, mock_db
    ):
        """Test getting non-existent constraint."""
        mock_db.get.return_value = None

        with pytest.raises(Exception) as exc_info:
            await constraint_service.get_constraint_by_id(
                mock_db, str(uuid4()), str(uuid4())
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_constraint_by_id_permission_denied(
        self,
        constraint_service,
        mock_db,
        mock_constraint,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
    ):
        """Test getting constraint without access."""
        mock_db.get.return_value = mock_constraint

        with (
            patch.object(
                constraint_service, "_get_field", return_value=mock_field
            ),
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service, "_get_workspace_member", return_value=None
            ),
        ):
            with pytest.raises(Exception) as exc_info:
                await constraint_service.get_constraint_by_id(
                    mock_db, mock_constraint.id, str(uuid4())
                )

            assert "access" in str(exc_info.value).lower()


class TestConstraintServiceList:
    """Test ConstraintService.list_constraints."""

    @pytest.mark.asyncio
    async def test_list_constraints_all(
        self, constraint_service, mock_db, mock_constraint
    ):
        """Test listing all constraints."""
        # Mock execute to return different results for count and data queries
        call_count = 0

        def execute_side_effect(query):
            nonlocal call_count
            result = MagicMock()
            call_count += 1
            if call_count == 1:  # Count query
                result.scalar.return_value = 1
            else:  # Data query
                result.scalars.return_value.all.return_value = [mock_constraint]
            return result

        mock_db.execute.side_effect = execute_side_effect

        constraints, total = await constraint_service.list_constraints(
            mock_db, None, str(uuid4())
        )

        assert len(constraints) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_constraints_by_field(
        self, constraint_service, mock_db, mock_constraint
    ):
        """Test listing constraints filtered by field."""
        call_count = 0

        def execute_side_effect(query):
            nonlocal call_count
            result = MagicMock()
            call_count += 1
            if call_count == 1:
                result.scalar.return_value = 1
            else:
                result.scalars.return_value.all.return_value = [mock_constraint]
            return result

        mock_db.execute.side_effect = execute_side_effect

        constraints, total = await constraint_service.list_constraints(
            mock_db, str(uuid4()), str(uuid4())
        )

        assert len(constraints) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_constraints_empty(
        self, constraint_service, mock_db
    ):
        """Test listing constraints with no results."""
        call_count = 0

        def execute_side_effect(query):
            nonlocal call_count
            result = MagicMock()
            call_count += 1
            if call_count == 1:
                result.scalar.return_value = 0
            else:
                result.scalars.return_value.all.return_value = []
            return result

        mock_db.execute.side_effect = execute_side_effect

        constraints, total = await constraint_service.list_constraints(
            mock_db, None, str(uuid4())
        )

        assert len(constraints) == 0
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_constraints_pagination(
        self, constraint_service, mock_db, mock_constraint
    ):
        """Test listing constraints with pagination."""
        call_count = 0

        def execute_side_effect(query):
            nonlocal call_count
            result = MagicMock()
            call_count += 1
            if call_count == 1:
                result.scalar.return_value = 50
            else:
                result.scalars.return_value.all.return_value = [mock_constraint]
            return result

        mock_db.execute.side_effect = execute_side_effect

        constraints, total = await constraint_service.list_constraints(
            mock_db, None, str(uuid4()), page=2, page_size=10
        )

        assert total == 50


class TestConstraintServiceUpdate:
    """Test ConstraintService.update_constraint."""

    @pytest.mark.asyncio
    async def test_update_constraint_status(
        self,
        constraint_service,
        mock_db,
        mock_constraint,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
        mock_workspace_member,
    ):
        """Test updating constraint status."""
        mock_db.get.return_value = mock_constraint

        with (
            patch.object(
                constraint_service, "get_constraint_by_id",
                return_value=mock_constraint
            ),
            patch.object(
                constraint_service, "_get_field", return_value=mock_field
            ),
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service,
                "_get_workspace_member",
                return_value=mock_workspace_member,
            ),
        ):
            update_data = UniqueConstraintUpdate(
                status=UniqueConstraintStatus.DISABLED.value
            )

            result = await constraint_service.update_constraint(
                mock_db, mock_constraint.id, mock_workspace_member.user_id, update_data
            )

            assert result.status == UniqueConstraintStatus.DISABLED.value
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_constraint_case_sensitive(
        self,
        constraint_service,
        mock_db,
        mock_constraint,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
        mock_workspace_member,
    ):
        """Test updating constraint case sensitivity."""
        mock_db.get.return_value = mock_constraint

        with (
            patch.object(
                constraint_service, "get_constraint_by_id",
                return_value=mock_constraint
            ),
            patch.object(
                constraint_service, "_get_field", return_value=mock_field
            ),
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service,
                "_get_workspace_member",
                return_value=mock_workspace_member,
            ),
        ):
            update_data = UniqueConstraintUpdate(case_sensitive=False)

            result = await constraint_service.update_constraint(
                mock_db, mock_constraint.id, mock_workspace_member.user_id, update_data
            )

            assert result.case_sensitive is False

    @pytest.mark.asyncio
    async def test_update_constraint_error_message(
        self,
        constraint_service,
        mock_db,
        mock_constraint,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
        mock_workspace_member,
    ):
        """Test updating constraint error message."""
        mock_db.get.return_value = mock_constraint

        with (
            patch.object(
                constraint_service, "get_constraint_by_id",
                return_value=mock_constraint
            ),
            patch.object(
                constraint_service, "_get_field", return_value=mock_field
            ),
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service,
                "_get_workspace_member",
                return_value=mock_workspace_member,
            ),
        ):
            update_data = UniqueConstraintUpdate(
                error_message="Custom error message"
            )

            result = await constraint_service.update_constraint(
                mock_db, mock_constraint.id, mock_workspace_member.user_id, update_data
            )

            assert result.error_message == "Custom error message"

    @pytest.mark.asyncio
    async def test_update_constraint_invalid_status(
        self,
        constraint_service,
        mock_db,
        mock_constraint,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
        mock_workspace_member,
    ):
        """Test updating constraint with invalid status."""
        mock_db.get.return_value = mock_constraint

        with (
            patch.object(
                constraint_service, "get_constraint_by_id",
                return_value=mock_constraint
            ),
            patch.object(
                constraint_service, "_get_field", return_value=mock_field
            ),
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service,
                "_get_workspace_member",
                return_value=mock_workspace_member,
            ),
        ):
            update_data = UniqueConstraintUpdate(status="invalid_status")

            with pytest.raises(Exception) as exc_info:
                await constraint_service.update_constraint(
                    mock_db, mock_constraint.id, mock_workspace_member.user_id, update_data
                )

            assert "invalid" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_constraint_permission_denied(
        self,
        constraint_service,
        mock_db,
        mock_constraint,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
    ):
        """Test updating constraint without admin permissions."""
        # Create member with viewer role
        member = MagicMock(spec=WorkspaceMember)
        member.role = WorkspaceRole.VIEWER

        mock_db.get.return_value = mock_constraint

        with (
            patch.object(
                constraint_service, "get_constraint_by_id",
                return_value=mock_constraint
            ),
            patch.object(
                constraint_service, "_get_field", return_value=mock_field
            ),
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
            patch.object(
                constraint_service, "_get_workspace_member", return_value=member
            ),
        ):
            update_data = UniqueConstraintUpdate(
                status=UniqueConstraintStatus.DISABLED.value
            )

            with pytest.raises(Exception) as exc_info:
                await constraint_service.update_constraint(
                    mock_db, mock_constraint.id, str(uuid4()), update_data
                )

            assert "can update" in str(exc_info.value).lower()


class TestConstraintServiceDelete:
    """Test ConstraintService.delete_constraint."""

    @pytest.mark.asyncio
    async def test_delete_constraint_success(
        self,
        constraint_service,
        mock_db,
        mock_constraint,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
    ):
        """Test successful constraint deletion."""
        mock_db.get.return_value = mock_constraint
        owner_id = str(uuid4())
        mock_workspace.owner_id = owner_id

        with (
            patch.object(
                constraint_service, "get_constraint_by_id",
                return_value=mock_constraint
            ),
            patch.object(
                constraint_service, "_get_field", return_value=mock_field
            ),
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
        ):
            await constraint_service.delete_constraint(
                mock_db, mock_constraint.id, owner_id
            )

            mock_db.delete.assert_called_once_with(mock_constraint)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_constraint_not_owner(
        self,
        constraint_service,
        mock_db,
        mock_constraint,
        mock_field,
        mock_table,
        mock_base,
        mock_workspace,
    ):
        """Test deleting constraint by non-owner."""
        owner_id = str(uuid4())
        mock_workspace.owner_id = owner_id
        mock_db.get.return_value = mock_constraint

        with (
            patch.object(
                constraint_service, "get_constraint_by_id",
                return_value=mock_constraint
            ),
            patch.object(
                constraint_service, "_get_field", return_value=mock_field
            ),
            patch.object(
                constraint_service, "_get_table", return_value=mock_table
            ),
            patch.object(
                constraint_service, "_get_base", return_value=mock_base
            ),
            patch.object(
                constraint_service, "_get_workspace", return_value=mock_workspace
            ),
        ):
            with pytest.raises(Exception) as exc_info:
                await constraint_service.delete_constraint(
                    mock_db, mock_constraint.id, str(uuid4())
                )

            assert "can delete" in str(exc_info.value).lower()


class TestConstraintServiceGetByField:
    """Test ConstraintService.get_constraint_by_field."""

    @pytest.mark.asyncio
    async def test_get_constraint_by_field_found(
        self, constraint_service, mock_db, mock_constraint
    ):
        """Test getting constraint by field when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_constraint
        mock_db.execute.return_value = mock_result

        result = await constraint_service.get_constraint_by_field(
            mock_db, str(uuid4())
        )

        assert result == mock_constraint

    @pytest.mark.asyncio
    async def test_get_constraint_by_field_not_found(
        self, constraint_service, mock_db
    ):
        """Test getting constraint by field when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await constraint_service.get_constraint_by_field(
            mock_db, str(uuid4())
        )

        assert result is None


class TestConstraintServiceHelpers:
    """Test ConstraintService private helper methods."""

    @pytest.mark.asyncio
    async def test_get_workspace_success(
        self, constraint_service, mock_db, mock_workspace
    ):
        """Test _get_workspace when workspace exists."""
        mock_db.get.return_value = mock_workspace

        result = await constraint_service._get_workspace(mock_db, mock_workspace.id)

        assert result == mock_workspace

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(self, constraint_service, mock_db):
        """Test _get_workspace when workspace not found."""
        mock_db.get.return_value = None

        with pytest.raises(Exception) as exc_info:
            await constraint_service._get_workspace(mock_db, str(uuid4()))

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_workspace_deleted(
        self, constraint_service, mock_db, mock_workspace
    ):
        """Test _get_workspace when workspace is deleted."""
        mock_workspace.is_deleted = True
        mock_db.get.return_value = mock_workspace

        with pytest.raises(Exception) as exc_info:
            await constraint_service._get_workspace(mock_db, mock_workspace.id)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_workspace_member_found(
        self, constraint_service, mock_db, mock_workspace_member
    ):
        """Test _get_workspace_member when member exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workspace_member
        mock_db.execute.return_value = mock_result

        result = await constraint_service._get_workspace_member(
            mock_db, mock_workspace_member.workspace_id, mock_workspace_member.user_id
        )

        assert result == mock_workspace_member

    @pytest.mark.asyncio
    async def test_get_workspace_member_not_found(
        self, constraint_service, mock_db
    ):
        """Test _get_workspace_member when member not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await constraint_service._get_workspace_member(
            mock_db, str(uuid4()), str(uuid4())
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_base_success(
        self, constraint_service, mock_db, mock_base
    ):
        """Test _get_base when base exists."""
        mock_db.get.return_value = mock_base

        result = await constraint_service._get_base(mock_db, mock_base.id)

        assert result == mock_base

    @pytest.mark.asyncio
    async def test_get_base_not_found(self, constraint_service, mock_db):
        """Test _get_base when base not found."""
        mock_db.get.return_value = None

        with pytest.raises(Exception) as exc_info:
            await constraint_service._get_base(mock_db, str(uuid4()))

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_base_deleted(
        self, constraint_service, mock_db, mock_base
    ):
        """Test _get_base when base is deleted."""
        mock_base.is_deleted = True
        mock_db.get.return_value = mock_base

        with pytest.raises(Exception) as exc_info:
            await constraint_service._get_base(mock_db, mock_base.id)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_table_success(
        self, constraint_service, mock_db, mock_table
    ):
        """Test _get_table when table exists."""
        mock_db.get.return_value = mock_table

        result = await constraint_service._get_table(mock_db, mock_table.id)

        assert result == mock_table

    @pytest.mark.asyncio
    async def test_get_table_not_found(self, constraint_service, mock_db):
        """Test _get_table when table not found."""
        mock_db.get.return_value = None

        with pytest.raises(Exception) as exc_info:
            await constraint_service._get_table(mock_db, str(uuid4()))

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_table_deleted(
        self, constraint_service, mock_db, mock_table
    ):
        """Test _get_table when table is deleted."""
        mock_table.is_deleted = True
        mock_db.get.return_value = mock_table

        with pytest.raises(Exception) as exc_info:
            await constraint_service._get_table(mock_db, mock_table.id)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_field_success(
        self, constraint_service, mock_db, mock_field
    ):
        """Test _get_field when field exists."""
        mock_db.get.return_value = mock_field

        result = await constraint_service._get_field(mock_db, mock_field.id)

        assert result == mock_field

    @pytest.mark.asyncio
    async def test_get_field_not_found(self, constraint_service, mock_db):
        """Test _get_field when field not found."""
        mock_db.get.return_value = None

        with pytest.raises(Exception) as exc_info:
            await constraint_service._get_field(mock_db, str(uuid4()))

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_field_deleted(
        self, constraint_service, mock_db, mock_field
    ):
        """Test _get_field when field is deleted."""
        mock_field.is_deleted = True
        mock_db.get.return_value = mock_field

        with pytest.raises(Exception) as exc_info:
            await constraint_service._get_field(mock_db, mock_field.id)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_constraint_by_field_found(
        self, constraint_service, mock_db, mock_constraint
    ):
        """Test _get_constraint_by_field when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_constraint
        mock_db.execute.return_value = mock_result

        result = await constraint_service._get_constraint_by_field(
            mock_db, str(uuid4())
        )

        assert result == mock_constraint

    @pytest.mark.asyncio
    async def test_get_constraint_by_field_not_found(
        self, constraint_service, mock_db
    ):
        """Test _get_constraint_by_field when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await constraint_service._get_constraint_by_field(
            mock_db, str(uuid4())
        )

        assert result is None
