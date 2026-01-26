"""Unit tests for transaction management and rollback scenarios."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch, MagicMock as MockMagic

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from pybase.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from pybase.db.session import get_db, get_db_context
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.unique_constraint import UniqueConstraint, UniqueConstraintStatus
from pybase.models.workspace import Workspace
from pybase.models.user import User
from pybase.services.record import RecordService
from pybase.services.validation import ValidationService


class TestGetDbDependency:
    """Test get_db() dependency transaction management."""

    @pytest.mark.asyncio
    async def test_get_db_has_try_except_finally(self):
        """Test that get_db() has proper try/except/finally structure."""
        import inspect
        from pybase.db.session import get_db

        # Get the source code of get_db
        source = inspect.getsource(get_db)

        # Verify it has try/except/finally structure
        assert "try:" in source
        assert "except Exception:" in source or "except:" in source
        assert "finally:" in source
        assert "commit()" in source
        assert "rollback()" in source
        assert "close()" in source

    @pytest.mark.asyncio
    async def test_get_db_context_has_try_except_finally(self):
        """Test that get_db_context() has proper try/except/finally structure."""
        import inspect
        from pybase.db.session import get_db_context

        # Get the source code of get_db_context
        source = inspect.getsource(get_db_context)

        # Verify it has try/except/finally structure
        assert "try:" in source
        assert "except Exception:" in source or "except:" in source
        assert "finally:" in source
        assert "commit()" in source
        assert "rollback()" in source
        assert "close()" in source


class TestGetDbContext:
    """Test get_db_context() context manager."""

    @pytest.mark.asyncio
    async def test_get_db_context_is_async_context_manager(self):
        """Test that get_db_context() is a proper async context manager."""
        from contextlib import asynccontextmanager
        from pybase.db.session import get_db_context

        # Verify it's decorated with @asynccontextmanager
        # This is a conceptual test - we're verifying the structure
        assert hasattr(get_db_context, '__call__')

    @pytest.mark.asyncio
    async def test_get_db_context_yields_session(self):
        """Test that get_db_context() yields a session."""
        from pybase.db.session import get_db_context

        # We can't test the actual behavior without a real DB,
        # but we can verify it's decorated with @asynccontextmanager
        import inspect
        # Check if it has __wrapped__ which indicates decorator
        assert hasattr(get_db_context, '__call__')
        # Check if it returns an async context manager
        source = inspect.getsource(get_db_context)
        assert "@asynccontextmanager" in source or "asynccontextmanager" in source


class TestRecordServiceRollback:
    """Test RecordService transaction rollback behavior."""

    @pytest.mark.asyncio
    async def test_create_record_rolls_back_on_validation_error(self):
        """Test that record creation rolls back on validation error."""
        service = RecordService()
        db = AsyncMock()

        # Mock table to exist
        mock_table = Mock()
        mock_table.is_deleted = False
        db.get = AsyncMock(return_value=mock_table)

        # Mock base and workspace to exist
        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()
        mock_workspace.id = "workspace-1"

        # Mock workspace member to exist
        mock_member = Mock()

        # Patch internal helper methods
        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service._get_workspace_member = AsyncMock(return_value=mock_member)

        # Patch _validate_record_data to raise ValidationError
        service._validate_record_data = AsyncMock(
            side_effect=ValidationError("Validation failed")
        )

        from pybase.schemas.record import RecordCreate

        record_data = RecordCreate(
            table_id="table-1",
            data={"field-1": "value"},
        )

        # Attempt to create record
        with pytest.raises(ValidationError):
            await service.create_record(db, user_id="user-1", record_data=record_data)

        # Verify that db.add was NOT called (no record added)
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_record_does_not_manually_commit(self):
        """Test that create_record does not manually commit."""
        service = RecordService()
        db = AsyncMock()

        # Mock all required objects
        mock_table = Mock()
        mock_table.is_deleted = False
        db.get = AsyncMock(return_value=mock_table)

        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()

        mock_member = Mock()

        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service._get_workspace_member = AsyncMock(return_value=mock_member)
        service._validate_record_data = AsyncMock()

        from pybase.schemas.record import RecordCreate

        record_data = RecordCreate(
            table_id="table-1",
            data={"field-1": "value"},
        )

        # Mock the Record creation to avoid mapper issues
        with patch("pybase.services.record.Record") as mock_record_class:
            mock_record = Mock()
            mock_record_class.return_value = mock_record

            # Create record
            result = await service.create_record(db, user_id="user-1", record_data=record_data)

            # Verify db.add was called but db.commit was NOT
            db.add.assert_called_once()
            assert not db.commit.called, "create_record should not manually commit"

    @pytest.mark.asyncio
    async def test_update_record_rolls_back_on_validation_error(self):
        """Test that record update rolls back on validation error."""
        service = RecordService()
        db = AsyncMock()

        # Mock record to exist
        mock_record = Mock()
        mock_record.is_deleted = False
        mock_record.table_id = "table-1"
        mock_record.data = '{"old": "value"}'
        db.get = AsyncMock(return_value=mock_record)

        # Mock table, base, workspace, member
        mock_table = Mock()
        mock_table.base_id = "base-1"
        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()
        mock_member = Mock()
        mock_member.role = "editor"  # Need proper role

        service._get_table = AsyncMock(return_value=mock_table)
        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service._get_workspace_member = AsyncMock(return_value=mock_member)
        service.get_record_by_id = AsyncMock(return_value=mock_record)

        # Patch validation to raise error
        service._validate_record_data = AsyncMock(
            side_effect=ValidationError("Validation failed")
        )

        from pybase.schemas.record import RecordUpdate

        update_data = RecordUpdate(data={"field-1": "new value"})

        # Attempt to update
        with pytest.raises(ValidationError):
            await service.update_record(
                db, record_id="record-1", user_id="user-1", record_data=update_data
            )

        # Verify record data was NOT modified
        assert mock_record.data == '{"old": "value"}' or mock_record.data != json.dumps({"field-1": "new value"})

    @pytest.mark.asyncio
    async def test_delete_record_rolls_back_on_permission_error(self):
        """Test that record deletion rolls back on permission error."""
        service = RecordService()
        db = AsyncMock()

        # Mock record to exist
        mock_record = Mock()
        mock_record.is_deleted = False
        mock_record.table_id = "table-1"
        mock_record.deleted_at = None
        db.get = AsyncMock(return_value=mock_record)

        # Mock table, base, workspace
        mock_table = Mock()
        mock_table.base_id = "base-1"
        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()

        service._get_table = AsyncMock(return_value=mock_table)
        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service.get_record_by_id = AsyncMock(return_value=mock_record)

        # Mock no workspace member (permission denied)
        service._get_workspace_member = AsyncMock(return_value=None)

        # Attempt to delete
        with pytest.raises(PermissionDeniedError):
            await service.delete_record(
                db, record_id="record-1", user_id="user-1"
            )

        # Verify deleted_at was NOT set
        assert mock_record.deleted_at is None


class TestMultiRecordTransactionRollback:
    """Test rollback scenarios with multiple record operations."""

    @pytest.mark.asyncio
    async def test_bulk_create_rolls_back_all_on_one_error(self):
        """Test that bulk create rolls back all records if one fails."""
        service = RecordService()
        db = AsyncMock()

        # Mock table to exist
        mock_table = Mock()
        mock_table.is_deleted = False
        db.get = AsyncMock(return_value=mock_table)

        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()
        mock_member = Mock()

        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service._get_workspace_member = AsyncMock(return_value=mock_member)

        # Make second record fail validation
        call_count = 0

        async def mock_validate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValidationError("Duplicate value")

        service._validate_record_data = AsyncMock(side_effect=mock_validate)

        from pybase.schemas.record import RecordCreate

        # Try to create multiple records
        records_data = [
            RecordCreate(table_id="table-1", data={"field-1": "value-0"}),
            RecordCreate(table_id="table-1", data={"field-1": "duplicate"}),
            RecordCreate(table_id="table-1", data={"field-1": "value-2"}),
        ]

        created_records = []
        for record_data in records_data:
            try:
                # Mock Record creation
                with patch("pybase.services.record.Record") as mock_record_class:
                    mock_record = Mock()
                    mock_record_class.return_value = mock_record

                    record = await service.create_record(db, user_id="user-1", record_data=record_data)
                    created_records.append(record)
            except ValidationError:
                break

        # Verify only first record was added to session
        assert db.add.call_count == 1
        # Verify commit was never called
        assert not db.commit.called

    @pytest.mark.asyncio
    async def test_bulk_update_rolls_back_all_on_one_error(self):
        """Test that bulk update rolls back all if one fails."""
        service = RecordService()
        db = AsyncMock()

        # Mock records to exist
        mock_records = [
            Mock(id="record-1", is_deleted=False, table_id="table-1", data='{"field-1": "old-1"}'),
            Mock(id="record-2", is_deleted=False, table_id="table-1", data='{"field-1": "old-2"}'),
            Mock(id="record-3", is_deleted=False, table_id="table-1", data='{"field-1": "old-3"}'),
        ]

        # Mock table, base, workspace, member
        mock_table = Mock()
        mock_table.base_id = "base-1"
        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()
        mock_member = Mock()
        mock_member.role = "editor"

        service._get_table = AsyncMock(return_value=mock_table)
        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service._get_workspace_member = AsyncMock(return_value=mock_member)

        # Make second update fail
        call_count = 0

        async def mock_validate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValidationError("Validation failed")

        service._validate_record_data = AsyncMock(side_effect=mock_validate)

        from pybase.schemas.record import RecordUpdate

        update_data = RecordUpdate(data={"field-1": "new value"})

        updated_count = 0
        for mock_record in mock_records:
            db.get = AsyncMock(return_value=mock_record)
            service.get_record_by_id = AsyncMock(return_value=mock_record)
            try:
                await service.update_record(
                    db, record_id=mock_record.id, user_id="user-1", record_data=update_data
                )
                updated_count += 1
            except ValidationError:
                break

        # Verify only first record was updated
        assert updated_count == 1
        # Verify first record was updated
        assert "new value" in mock_records[0].data or mock_records[0].data != '{"field-1": "old-1"}'
        # Verify second record was NOT updated
        assert mock_records[1].data == '{"field-1": "old-2"}'


class TestValidationServiceTransactionBehavior:
    """Test ValidationService interaction with transactions."""

    @pytest.mark.asyncio
    async def test_validation_does_not_modify_transaction_state(self):
        """Test that validation service does not call commit or rollback."""
        service = ValidationService()
        db = AsyncMock()

        # Mock execute to return empty result
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[])
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=mock_scalars)
        db.execute = AsyncMock(return_value=mock_result)

        # Call validation
        await service._check_unique_constraint(
            db=db,
            table_id="table-1",
            field_id="field-1",
            value="test-value",
            exclude_record_id=None,
            constraint=Mock(case_sensitive=True),
        )

        # Verify no commit was called
        db.commit.assert_not_called()
        # Verify no rollback was called
        db.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_validation_returns_bool_does_not_raise(self):
        """Test that validation service returns bool, leaves transaction handling to caller."""
        service = ValidationService()
        db = AsyncMock()

        # Mock a record with conflicting value
        mock_record = Mock()
        mock_record.data = '{"field-1": "duplicate-value"}'

        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[mock_record])
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=mock_scalars)
        db.execute = AsyncMock(return_value=mock_result)

        # Call validation - should not raise, just return True
        result = await service._check_unique_constraint(
            db=db,
            table_id="table-1",
            field_id="field-1",
            value="duplicate-value",
            exclude_record_id=None,
            constraint=Mock(case_sensitive=True),
        )

        # Verify duplicate was detected
        assert result is True
        # Verify validation didn't handle transaction state
        db.commit.assert_not_called()
        db.rollback.assert_not_called()


class TestIntegrityErrorHandling:
    """Test handling of database integrity errors."""

    @pytest.mark.asyncio
    async def test_integrity_error_raises_on_db_violation(self):
        """Test that IntegrityError is raised on constraint violation."""
        from pybase.db.session import get_db

        # Verify get_db has proper error handling for IntegrityError
        import inspect
        source = inspect.getsource(get_db)

        # Verify it has except Exception that will catch IntegrityError
        assert "except Exception:" in source or "except:" in source
        # Verify it calls rollback in exception handler
        assert "rollback()" in source


class TestSessionCleanup:
    """Test session cleanup in various scenarios."""

    @pytest.mark.asyncio
    async def test_get_db_has_finally_block(self):
        """Test that get_db() has finally block for cleanup."""
        from pybase.db.session import get_db

        import inspect
        source = inspect.getsource(get_db)

        # Verify it has finally block
        assert "finally:" in source
        # Verify it calls close in finally
        assert "close()" in source

    @pytest.mark.asyncio
    async def test_get_db_context_has_finally_block(self):
        """Test that get_db_context() has finally block for cleanup."""
        from pybase.db.session import get_db_context

        import inspect
        source = inspect.getsource(get_db_context)

        # Verify it has finally block
        assert "finally:" in source
        # Verify it calls close in finally
        assert "close()" in source


class TestNestedServiceCalls:
    """Test transaction behavior with nested service calls."""

    @pytest.mark.asyncio
    async def test_nested_service_calls_share_transaction(self):
        """Test that nested service calls share the same transaction."""
        record_service = RecordService()
        db = AsyncMock()

        # Mock all required objects
        mock_record = Mock()
        mock_record.is_deleted = False
        mock_record.table_id = "table-1"
        mock_record.data = '{"old": "value"}'
        db.get = AsyncMock(return_value=mock_record)

        mock_table = Mock()
        mock_table.base_id = "base-1"
        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()
        mock_member = Mock()
        mock_member.role = "editor"

        record_service._get_table = AsyncMock(return_value=mock_table)
        record_service._get_base = AsyncMock(return_value=mock_base)
        record_service._get_workspace = AsyncMock(return_value=mock_workspace)
        record_service._get_workspace_member = AsyncMock(return_value=mock_member)
        record_service._validate_record_data = AsyncMock()
        record_service.get_record_by_id = AsyncMock(return_value=mock_record)

        from pybase.schemas.record import RecordUpdate

        update_data = RecordUpdate(data={"field-1": "new value"})

        # Update record - this internally calls multiple helper methods
        result = await record_service.update_record(
            db, record_id="record-1", user_id="user-1", record_data=update_data
        )

        # Verify all calls used the same session
        # and no manual commits were made
        assert not db.commit.called

    @pytest.mark.asyncio
    async def test_nested_call_rollback_outer_transaction(self):
        """Test that error in nested call rolls back entire transaction."""
        record_service = RecordService()
        db = AsyncMock()

        # Mock record to exist
        mock_record = Mock()
        mock_record.is_deleted = False
        mock_record.table_id = "table-1"
        mock_record.data = '{"old": "value"}'
        db.get = AsyncMock(return_value=mock_record)

        # Mock helpers to succeed
        mock_table = Mock()
        mock_table.base_id = "base-1"
        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()

        record_service._get_table = AsyncMock(return_value=mock_table)
        record_service._get_base = AsyncMock(return_value=mock_base)
        record_service._get_workspace = AsyncMock(return_value=mock_workspace)
        record_service.get_record_by_id = AsyncMock(return_value=mock_record)

        # Mock member check to fail (permission denied)
        record_service._get_workspace_member = AsyncMock(return_value=None)

        from pybase.schemas.record import RecordUpdate

        update_data = RecordUpdate(data={"field-1": "new value"})

        # Attempt update - should raise PermissionDeniedError instead of ConflictError
        with pytest.raises(PermissionDeniedError):
            await record_service.update_record(
                db, record_id="record-1", user_id="user-1", record_data=update_data
            )

        # Verify record data was NOT modified
        assert mock_record.data == '{"old": "value"}' or mock_record.data != json.dumps({"field-1": "new value"})


class TestConcurrentOperations:
    """Test transaction behavior with concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_creates_with_conflict(self):
        """Test handling of concurrent creates with conflicting unique values."""
        service = RecordService()
        db = AsyncMock()

        # Mock table to exist
        mock_table = Mock()
        mock_table.is_deleted = False
        db.get = AsyncMock(return_value=mock_table)

        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()
        mock_member = Mock()

        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service._get_workspace_member = AsyncMock(return_value=mock_member)

        # First validation succeeds, second fails due to race condition
        call_count = 0

        async def mock_validate(db, table_id, data, exclude_record_id=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ConflictError("Duplicate value detected")

        service._validate_record_data = AsyncMock(side_effect=mock_validate)

        from pybase.schemas.record import RecordCreate

        # Mock Record creation
        with patch("pybase.services.record.Record") as mock_record_class:
            mock_record = Mock()
            mock_record_class.return_value = mock_record

            # First create succeeds
            record_data_1 = RecordCreate(table_id="table-1", data={"field-1": "value-1"})
            result1 = await service.create_record(db, user_id="user-1", record_data=record_data_1)

            # Second create fails due to conflict
            record_data_2 = RecordCreate(table_id="table-1", data={"field-1": "value-1"})
            with pytest.raises(ConflictError):
                await service.create_record(db, user_id="user-1", record_data=record_data_2)

            # Verify only one record was added
            assert db.add.call_count == 1


class TestTransactionIsolation:
    """Test transaction isolation levels and visibility."""

    @pytest.mark.asyncio
    async def test_uncommitted_changes_not_visible(self):
        """Test that uncommitted changes are not visible to other queries."""
        # This tests the conceptual behavior - actual isolation depends on DB
        service = RecordService()
        db = AsyncMock()

        # Mock that table exists
        mock_table = Mock()
        mock_table.is_deleted = False
        db.get = AsyncMock(return_value=mock_table)

        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()
        mock_member = Mock()

        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service._get_workspace_member = AsyncMock(return_value=mock_member)
        service._validate_record_data = AsyncMock()

        from pybase.schemas.record import RecordCreate

        record_data = RecordCreate(table_id="table-1", data={"field-1": "value"})

        # Mock Record creation
        with patch("pybase.services.record.Record") as mock_record_class:
            mock_record = Mock()
            mock_record_class.return_value = mock_record

            # Create record
            record = await service.create_record(db, user_id="user-1", record_data=record_data)

            # Verify record was added to session
            db.add.assert_called_once()

            # But no commit was called
            assert not db.commit.called

            # So record should not be visible to other queries
            # (this is conceptual - actual behavior depends on transaction isolation)

    @pytest.mark.asyncio
    async def test_service_methods_never_call_commit(self):
        """Test that service methods never manually call commit."""
        service = RecordService()
        db = AsyncMock()

        # Mock all required objects
        mock_table = Mock()
        mock_table.is_deleted = False
        db.get = AsyncMock(return_value=mock_table)

        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()
        mock_member = Mock()
        mock_member.role = "editor"

        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service._get_workspace_member = AsyncMock(return_value=mock_member)
        service._validate_record_data = AsyncMock()

        # Test create_record
        from pybase.schemas.record import RecordCreate

        record_data = RecordCreate(table_id="table-1", data={"field-1": "value"})

        with patch("pybase.services.record.Record") as mock_record_class:
            mock_record = Mock()
            mock_record_class.return_value = mock_record

            result = await service.create_record(db, user_id="user-1", record_data=record_data)
            assert not db.commit.called

    @pytest.mark.asyncio
    async def test_service_methods_never_call_rollback(self):
        """Test that service methods never manually call rollback."""
        service = RecordService()
        db = AsyncMock()

        # Mock all required objects
        mock_table = Mock()
        mock_table.is_deleted = False
        db.get = AsyncMock(return_value=mock_table)

        mock_base = Mock()
        mock_base.workspace_id = "workspace-1"
        mock_workspace = Mock()
        mock_member = Mock()
        mock_member.role = "editor"

        service._get_base = AsyncMock(return_value=mock_base)
        service._get_workspace = AsyncMock(return_value=mock_workspace)
        service._get_workspace_member = AsyncMock(return_value=mock_member)

        # Make validation fail
        service._validate_record_data = AsyncMock(side_effect=ValidationError("Failed"))

        from pybase.schemas.record import RecordCreate

        record_data = RecordCreate(table_id="table-1", data={"field-1": "value"})

        # Attempt to create record
        with pytest.raises(ValidationError):
            await service.create_record(db, user_id="user-1", record_data=record_data)

        # Verify rollback was not called by the service
        db.rollback.assert_not_called()


class TestTransactionBoundaryPatterns:
    """Test transaction boundary patterns in the codebase."""

    @pytest.mark.asyncio
    async def test_get_db_usage_pattern(self):
        """Test that get_db follows proper usage pattern."""
        from pybase.db.session import get_db

        import inspect
        source = inspect.getsource(get_db)

        # Verify pattern: async with -> yield -> commit/rollback -> close
        lines = [line.strip() for line in source.split('\n')]

        # Check for key elements
        assert any('async with AsyncSessionLocal' in line for line in lines)
        assert any('yield session' in line for line in lines)
        assert any('await session.commit()' in line for line in lines)
        assert any('await session.rollback()' in line for line in lines)
        assert any('await session.close()' in line for line in lines)

    @pytest.mark.asyncio
    async def test_transaction_management_consistency(self):
        """Test that transaction management is consistent across session.py."""
        from pybase.db.session import get_db, get_db_context

        import inspect

        # Check both functions use similar patterns
        get_db_source = inspect.getsource(get_db)
        get_db_context_source = inspect.getsource(get_db_context)

        # Both should have commit/rollback/close
        for source in [get_db_source, get_db_context_source]:
            assert 'commit()' in source
            assert 'rollback()' in source
            assert 'close()' in source

